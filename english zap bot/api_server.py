"""
╔══════════════════════════════════════════════════════════════╗
  ⚡ English Zap — API Server
  Bridges the webapp with Edge TTS and Telegram bot data.

  pip install fastapi uvicorn edge-tts python-multipart
  python api_server.py
╚══════════════════════════════════════════════════════════════╝
"""

import io
import os
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel

app = FastAPI(title="English Zap API", version="1.0")

# Allow the webapp (any origin locally)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Paths ───────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
WEBAPP_HTML = BASE_DIR / "english_zap_webapp.html"
LOGO_IMG = BASE_DIR / "logo.jpeg"

BOT_DATA_FILE = Path(os.getenv("ENGLISH_ZAP_DATA_FILE", str(BASE_DIR / "english_zap_bot_data.json")))
WORDS_DIR = Path(os.getenv("ENGLISH_ZAP_WORDS_DIR", str(PROJECT_ROOT / "user_words")))  # folder for per-user word JSONs
DEFAULT_VOICE = "en-GB-RyanNeural"

WORDS_DIR.mkdir(parents=True, exist_ok=True)


# ╔══════════════════════════════════════════════════════════════╗
#  EDGE TTS
# ╚══════════════════════════════════════════════════════════════╝

class TtsRequest(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE


class ProgressPayload(BaseModel):
    activity: dict = {}
    streak: int = 0
    lastDate: str = ""


@app.post("/tts")
async def tts_endpoint(req: TtsRequest):
    """Convert text to MP3 using Edge TTS and stream it."""
    try:
        communicate = edge_tts.Communicate(req.text, req.voice)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=audio.mp3"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")


# ╔══════════════════════════════════════════════════════════════╗
#  USER WORDS — Telegram sync
# ╚══════════════════════════════════════════════════════════════╝

def _user_words_path(user_id: str) -> str:
    return WORDS_DIR / f"words_{user_id}.json"


def _load_user_data(user_id: str) -> dict:
    path = _user_words_path(user_id)
    if not path.exists():
        return {"user_id": user_id, "words": [], "activity": {}, "streak": 0, "lastDate": ""}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        data = {"user_id": user_id, "words": []}
    data.setdefault("user_id", user_id)
    data.setdefault("words", [])
    data.setdefault("activity", {})
    data.setdefault("streak", 0)
    data.setdefault("lastDate", "")
    return data


def _save_user_data(user_id: str, data: dict) -> None:
    path = _user_words_path(user_id)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.get("/user_words/{user_id}")
async def get_user_words(user_id: str):
    """
    Return all words this user has received from the Telegram bot.
    The Telegram bot should write to WORDS_DIR/words_{user_id}.json
    whenever it sends a word to a user.
    """
    data = _load_user_data(user_id)
    return JSONResponse(data)


@app.post("/user_words/{user_id}")
async def add_user_word(user_id: str, payload: dict):
    """
    Called by the Telegram bot (or manually) to record a word for a user.
    Payload: {
        word,
        info: {
            emoji, transcribe, definition, ukrainian,
            pron_ua, example, example_uk
        },
        level
    }
    """
    data = _load_user_data(user_id)

    # Avoid duplicates
    existing = {w["word"] for w in data["words"] if isinstance(w, dict) and "word" in w}
    if payload.get("word") not in existing:
        data["words"].append({
            "word":    payload.get("word"),
            "info":    payload.get("info", {}),
            "level":   payload.get("level", "beginner"),
            "source":  "telegram",
            "addedAt": payload.get("addedAt"),
        })
        _save_user_data(user_id, data)
    return {"ok": True, "total": len(data["words"])}


@app.delete("/user_words/{user_id}")
async def delete_user_word(user_id: str, word: str = Query(...)):
    """Delete a word from user's server dictionary (case-insensitive, trimmed)."""
    key = str(word or "").strip().lower()
    if not key:
        raise HTTPException(status_code=400, detail="word is required")

    data = _load_user_data(user_id)
    before = len(data.get("words", []))

    def _norm(v) -> str:
        return str(v or "").strip().lower()

    data["words"] = [
        w for w in data.get("words", [])
        if not isinstance(w, dict) or _norm(w.get("word")) != key
    ]
    removed = before - len(data["words"])
    if removed > 0:
        _save_user_data(user_id, data)
    return {"ok": True, "removed": removed, "total": len(data["words"])}


@app.put("/user_words/{user_id}")
async def push_user_words(user_id: str, payload: dict):
    """
    Called by the webapp to push its full local word list (including SRS state).
    Merges with server data — for each word, keeps the version with the most
    repetitions so progress never goes backwards across devices.
    """
    incoming_words = payload.get("words", [])
    if not isinstance(incoming_words, list):
        raise HTTPException(status_code=400, detail="'words' must be a list")

    server_data = _load_user_data(user_id)
    server_map: dict = {}
    for w in server_data.get("words", []):
        if isinstance(w, dict) and w.get("word"):
            server_map[w["word"].strip().lower()] = w

    merged_count = 0
    for iw in incoming_words:
        if not isinstance(iw, dict) or not iw.get("word"):
            continue
        key = iw["word"].strip().lower()
        existing = server_map.get(key)
        if existing is None:
            # New word not on server yet — add it
            server_map[key] = iw
            merged_count += 1
        else:
            # Keep whichever has more repetitions (= more studied)
            existing_reps = int(existing.get("repetitions") or 0)
            incoming_reps = int(iw.get("repetitions") or 0)
            if incoming_reps >= existing_reps:
                # Incoming is more up-to-date — overwrite SRS fields only
                existing.update({
                    "repetitions": iw.get("repetitions", existing_reps),
                    "ef":          iw.get("ef",          existing.get("ef", 2.5)),
                    "nextReview":  iw.get("nextReview",  existing.get("nextReview")),
                    "lastRated":   iw.get("lastRated",   existing.get("lastRated")),
                    "intervalDays":iw.get("intervalDays",existing.get("intervalDays")),
                    "srsStatus":   iw.get("srsStatus",   existing.get("srsStatus")),
                    "mastered":    iw.get("mastered",    existing.get("mastered", False)),
                    # Keep info/level/source from whichever has it
                    "info":        iw.get("info") or existing.get("info", {}),
                    "level":       iw.get("level") or existing.get("level", "beginner"),
                })
                merged_count += 1

    server_data["words"] = list(server_map.values())
    _save_user_data(user_id, server_data)
    return {"ok": True, "total": len(server_data["words"]), "merged": merged_count}




@app.get("/user_progress/{user_id}")
async def get_user_progress(user_id: str):
    data = _load_user_data(user_id)
    return JSONResponse({
        "user_id": user_id,
        "activity": data.get("activity", {}),
        "streak": data.get("streak", 0),
        "lastDate": data.get("lastDate", ""),
    })


@app.post("/user_progress/{user_id}")
async def save_user_progress(user_id: str, payload: ProgressPayload):
    data = _load_user_data(user_id)
    data["activity"] = payload.activity if isinstance(payload.activity, dict) else {}
    data["streak"] = int(payload.streak or 0)
    data["lastDate"] = str(payload.lastDate or "")
    _save_user_data(user_id, data)
    return {"ok": True}


# ╔══════════════════════════════════════════════════════════════╗
#  BOT STATUS
# ╚══════════════════════════════════════════════════════════════╝

@app.get("/bot_status")
async def bot_status():
    """Returns basic info from the main bot data file."""
    if not BOT_DATA_FILE.exists():
        return {"ok": False, "message": "Bot data file not found", "users": 0}
    with BOT_DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "ok": True,
        "users": len(data.get("user_chat_ids", [])),
        "levels": data.get("user_levels", {}),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "English Zap API"}


@app.get("/")
async def root():
    """Serve the webapp when accessed from browser (macOS local use)."""
    if WEBAPP_HTML.exists():
        return FileResponse(WEBAPP_HTML, media_type="text/html")
    return {"status": "ok", "message": "English Zap API — add english_zap_webapp.html for webapp"}

@app.get("/logo.jpeg")
async def logo():
    """Serve the logo image for the webapp."""
    if LOGO_IMG.exists():
        return FileResponse(LOGO_IMG, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Logo not found")

# ╔══════════════════════════════════════════════════════════════╗
#  RUN
# ╚══════════════════════════════════════════════════════════════╝
if __name__ == "__main__":
    import uvicorn
    print("⚡ English Zap API Server")
    print(f"   TTS voice : {DEFAULT_VOICE}")
    print(f"   Words dir : {WORDS_DIR}")
    print(f"   Bot data  : {BOT_DATA_FILE}")
    print("   Listening  : http://localhost:8765")
    print("   Webapp     : http://localhost:8765/")
    uvicorn.run(app, host="0.0.0.0", port=8765)
