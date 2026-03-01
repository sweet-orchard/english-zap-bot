"""
╔══════════════════════════════════════════════════════════════╗
  ⚡ English Zap Bot — v3 with Telegram Mini App support

  pip install python-telegram-bot httpx edge-tts
  python english_zap_bot.py
╚══════════════════════════════════════════════════════════════╝
"""

import re
import io
import os
import json
import httpx

import random
import asyncio
import logging
import socket
from pathlib import Path
from datetime import datetime, time, timezone

# Load .env file properly
from dotenv import load_dotenv
load_dotenv()
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, WebAppInfo, MenuButtonWebApp,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes,
)
from telegram.error import TelegramError

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("EnglishZap")

# ─── CONFIG ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

BOT_TOKEN = os.getenv("ENGLISH_ZAP_BOT_TOKEN", "").strip()
GEMINI_KEY = os.getenv("ENGLISH_ZAP_GEMINI_KEY", "").strip()
GEMINI_MODEL = os.getenv("ENGLISH_ZAP_GEMINI_MODEL", "gemini-1.5-flash").strip()
OWNER_CHAT_ID = int(os.getenv("ENGLISH_ZAP_OWNER_CHAT_ID", "861217697"))
VOICE = os.getenv("ENGLISH_ZAP_VOICE", "en-GB-RyanNeural")

# UPDATE THIS to your webapp URL (Cloudflare tunnel or nginx)
# e.g. https://contents-transparency-construct-brunette.trycloudflare.com
WEBAPP_URL = os.getenv("ENGLISH_ZAP_WEBAPP_URL", "https://YOUR_TUNNEL_URL_HERE").strip()

DATA_FILE = Path(os.getenv("ENGLISH_ZAP_DATA_FILE", str(BASE_DIR / "english_zap_bot_data.json")))
WORDS_DIR = Path(os.getenv("ENGLISH_ZAP_WORDS_DIR", str(PROJECT_ROOT / "user_words")))
WORDS_DIR.mkdir(parents=True, exist_ok=True)

# ─── DATA ─────────────────────────────────────────────────────


def load_data():
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                user_levels_data = data.get("user_levels", {})
                user_chat_ids_data = data.get("user_chat_ids", [])
                if not isinstance(user_levels_data, dict):
                    user_levels_data = {}
                if not isinstance(user_chat_ids_data, list):
                    user_chat_ids_data = []
                return user_levels_data, set(user_chat_ids_data)
        except Exception as e:
            logger.error(f"[load_data] {e}")
    return {}, set()


def save_data():
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump({"user_levels": user_levels, "user_chat_ids": list(
                user_chat_ids)}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[save_data] {e}")


user_levels, user_chat_ids = load_data()


def get_user_level(user_id: int) -> str:
    """Get level for user, checking both str and int keys (backwards compat)."""
    level = user_levels.get(str(user_id), user_levels.get(user_id, "beginner"))
    return str(level) if level else "beginner"

# ─── WORD SYNC ────────────────────────────────────────────────


def record_word_for_user(user_id: int, word: str, info: dict, level: str):
    """Save word to per-user sync file. Thread-safe via temp file + rename."""
    path = WORDS_DIR / f"words_{user_id}.json"
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"user_id": user_id, "words": []}

        words_list = data.get("words", [])
        if not isinstance(words_list, list):
            words_list = []
            data["words"] = words_list

        existing = {w["word"] for w in words_list if isinstance(w, dict) and "word" in w}
        if word not in existing:
            data["words"].append({
                "word": word,
                "info": info,
                "level": level,
                "source": "telegram",
                "addedAt": int(datetime.now(timezone.utc).timestamp() * 1000),
            })
            tmp = path.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)  # atomic rename
            logger.info(f"Recorded word '{word}' for user {user_id}")
    except Exception as e:
        logger.error(f"[record_word] user={user_id} word={word}: {e}")


def get_user_word_count(user_id: int) -> int:
    path = WORDS_DIR / f"words_{user_id}.json"
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                words = json.load(f).get("words", [])
                return len(words) if isinstance(words, list) else 0
    except BaseException:
        pass
    return 0

# ─── EDGE TTS ─────────────────────────────────────────────────


async def text_to_voice(text: str) -> io.BytesIO:
    import edge_tts
    voices_to_try = [VOICE, "en-US-AriaNeural", "en-GB-SoniaNeural"]
    last_error = None

    for voice in voices_to_try:
        for _ in range(2):
            try:
                communicate = edge_tts.Communicate(text, voice)
                buf = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buf.write(chunk["data"])
                if buf.tell() > 0:
                    buf.seek(0)
                    buf.name = "audio.mp3"
                    return buf
            except Exception as e:
                last_error = e
                await asyncio.sleep(0.4)

    raise RuntimeError(f"Edge TTS unavailable: {last_error}")

# ─── WORD FETCHING ─────────────────────────────────────────────


async def fetch_word_for_level(level: str) -> str:
    if level == "zero":
        return random.choice(["the",
                              "a",
                              "is",
                              "are",
                              "am",
                              "and",
                              "or",
                              "but",
                              "in",
                              "on",
                              "at",
                              "to",
                              "for",
                              "of",
                              "with",
                              "have",
                              "it",
                              "this",
                              "that",
                              "be",
                              "do",
                              "go",
                              "come",
                              "see",
                              "get",
                              "can",
                              "you",
                              "he",
                              "she",
                              "we",
                              "they",
                              "my",
                              "what",
                              "who",
                              "how",
                              "when",
                              "why",
                              ])
    cfg = {
        "beginner": {
            "topics": [
                "food",
                "home",
                "family",
                "animals",
                "body",
                "weather",
                "school",
                "colors"],
            "minF": 10,
            "maxF": 9999,
            "minL": 2,
            "maxL": 8},
        "intermediate": {
            "topics": [
                "travel",
                "work",
                "health",
                "money",
                "technology",
                "society",
                "emotion",
                "nature"],
            "minF": 1,
            "maxF": 50,
            "minL": 6,
            "maxL": 12},
        "advanced": {
            "topics": [
                "philosophy",
                "literature",
                "science",
                "rhetoric",
                "psychology"],
            "minF": 0.01,
            "maxF": 2,
            "minL": 8,
            "maxL": 20},
    }.get(
        level,
        {
            "topics": [
                "food",
                "home"],
            "minF": 5,
            "maxF": 9999,
            "minL": 3,
            "maxL": 8})

    topic = random.choice(cfg["topics"])
    fallback = [
        "hello",
        "world",
        "cat",
        "dog",
        "book",
        "time",
        "water",
        "day",
        "house",
        "tree"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://api.datamuse.com/words", params={"ml": topic, "md": "f", "max": 100})
            resp.raise_for_status()
            words = resp.json()
        filtered = []
        for item in words:
            w = item.get("word", "")
            for tag in item.get("tags", []):
                if tag.startswith("f:"):
                    freq = float(tag[2:])
                    if cfg["minF"] < freq < cfg["maxF"] and cfg["minL"] <= len(
                            w) <= cfg["maxL"] and w.isalpha():
                        filtered.append(w)
                    break
        if filtered:
            return random.choice(filtered)
    except Exception as e:
        logger.warning(f"[fetch_word] {e}")
    return random.choice(fallback)


async def fetch_phrase_for_level(level: str) -> str:
    phrases = {
        "zero": [
            "I am",
            "You are",
            "It is",
            "I have",
            "I go",
            "I like",
            "What is this?",
            "How are you?"],
        "beginner": [
            "How are you?",
            "Nice to meet you",
            "Thank you very much",
            "I don't understand",
            "Can you help me?"],
        "intermediate": [
            "I've been thinking about it",
            "What would you recommend?",
            "I'm looking forward to it"],
        "advanced": [
            "Actions speak louder than words",
            "Every cloud has a silver lining",
            "Practice makes perfect"],
    }
    return random.choice(phrases.get(level, phrases["beginner"]))

# ─── GEMINI ───────────────────────────────────────────────────


async def ask_gemini(word: str, level: str) -> dict:
    def fallback_info(reason: str) -> dict:
        logger.warning(f"[Gemini fallback] word={word} reason={reason}")
        return {
            "emoji": "📘",
            "transcribe": f"/{word.lower()}/",
            "definition": f"A useful English word or phrase: {word}.",
            "ukrainian": "Переклад тимчасово недоступний.",
            "pron_ua": word.lower(),
            "example": f"I can use '{word}' in a simple sentence.",
            "example_uk": f"Я можу використати '{word}' у простому реченні.",
        }

    def extract_label(text: str, label: str) -> str:
        # Accept plain labels and markdown-styled variants like "**LABEL:** value"
        patterns = [
            rf"(?im)^\s*\*{{0,2}}{re.escape(label)}\*{{0,2}}\s*:\s*(.+?)\s*$",
            rf"(?im)^\s*[-•]?\s*\*{{0,2}}{re.escape(label)}\*{{0,2}}\s*:\s*(.+?)\s*$",
        ]
        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                value = m.group(1).strip().strip("*_`")
                if value:
                    return value
        return ""

    if not GEMINI_KEY:
        info = fallback_info("missing_api_key")
        info["definition"] = "Gemini API key is missing."
        info["ukrainian"] = "Ключ Gemini не налаштований."
        return info

    logger.info(f"Using Gemini Key: {GEMINI_KEY[:8]}...{GEMINI_KEY[-4:]} (Model: {GEMINI_MODEL})")

    hint = {
        "zero": "Use extremely simple Ukrainian. Max 1 very short sentence.",
        "beginner": "Use simple Ukrainian. Provide a clear, detailed definition.",
        "intermediate": "Use natural Ukrainian. Provide a deep, comprehensive definition.",
        "advanced": "Use sophisticated Ukrainian. Provide a very detailed, nuanced definition.",
    }.get(level, "Use clear Ukrainian.")
    prompt = f"""You are an English learning assistant for Ukrainian speakers.
Explain the English word or phrase: "{word}"
Target Level: {level}
Instructions: {hint}
The DEFINITION must be in Ukrainian, detailed, and informative.

Reply ONLY in this exact format:
EMOJI: (one related emoji)
TRANSCRIBE: (IPA pronunciation)
DEFINITION: (detailed explanation in UKRAINIAN)
TRANSLATION: (Ukrainian translation of the word)
PRON_UA: (pronunciation using Ukrainian letters)
EXAMPLE: (English sentence using the word)
EXAMPLE_UK: (Ukrainian translation of the example)"""

    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {
        "temperature": 0.7, "maxOutputTokens": 1500}}
    models_to_try = list(dict.fromkeys([
        GEMINI_MODEL, 
        "gemini-2.5-flash", 
        "gemini-2.0-flash", 
        "gemini-flash-latest",
        "gemini-1.5-flash", 
        "gemini-2.5-pro",
        "gemini-1.5-pro"
    ]))
    api_versions = ["v1beta", "v1"]
    try:
        resp = None
        last_error = None
        last_network_error = None
        for api_ver in api_versions:
            for model in models_to_try:
                url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{model}:generateContent?key={GEMINI_KEY}"
                try:
                    async with httpx.AsyncClient(timeout=25) as client:
                        resp = await client.post(url, json=body)
                        data = resp.json()
                        if resp.status_code != 200 or "error" in data:
                            msg = data.get("error", {}).get("message", "Unknown error")
                            logger.warning(f"Gemini {resp.status_code} with {model}: {msg}")
                            last_error = Exception(f"{resp.status_code}: {msg}")
                            continue
                        # Success!
                        break
                except Exception as e:
                    last_network_error = e
                    logger.warning(f"Network error with {model}: {e}")
                    continue
            if resp and resp.status_code == 200:
                break

        if not resp or resp.status_code != 200:
            if last_error:
                raise last_error
            if last_network_error:
                raise last_network_error
            raise RuntimeError("Gemini request failed.")
        data = resp.json()
        if "error" in data:
            raise Exception(data["error"].get("message", "Unknown error"))
        cands = data.get("candidates") or []
        if not cands:
            raise Exception("Response blocked or empty. Try a different word.")
        text = cands[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not text:
            raise Exception("Response blocked or empty. Try a different word.")
        parsed = {
            "emoji": extract_label(text, "EMOJI"),
            "transcribe": extract_label(text, "TRANSCRIBE"),
            "definition": extract_label(text, "DEFINITION"),
            "ukrainian": extract_label(text, "TRANSLATION"),
            "pron_ua": extract_label(text, "PRON_UA"),
            "example": extract_label(text, "EXAMPLE"),
            "example_uk": extract_label(text, "EXAMPLE_UK"),
        }

        # If model didn't follow structure, avoid returning empty placeholders.
        missing = [k for k, v in parsed.items() if not v]
        if missing:
            fallback = fallback_info(f"missing_fields={','.join(missing)}")
            for key in missing:
                parsed[key] = fallback[key]
            if len(missing) >= 4:
                logger.warning(f"[Gemini raw text] {text[:800]}")
        return parsed
    except Exception as e:
        logger.error(f"[Gemini] {e}")
        message = str(e).lower()
        err_str = str(e)
        if ("name or service not known" in message or
            "nodename nor servname provided" in message or
            isinstance(e, socket.gaierror)):
            user_definition = "Немає DNS/інтернет доступу до Gemini."
            user_translation = "Перевірте підключення до інтернету."
        elif "403" in err_str or "permission denied" in message:
            user_definition = "403: Увімкніть Generative Language API в console.cloud.google.com та перевірте ключ."
            user_translation = err_str
        elif "400" in err_str and ("location" in message or "supported" in message):
            user_definition = "400: API недоступний у вашому регіоні. Увімкніть оплату або спробуйте інший регіон."
            user_translation = err_str
        elif "400" in err_str and "billing" in message:
            user_definition = "400: Потрібна оплата. Увімкніть billing в Google AI Studio."
            user_translation = err_str
        elif "401" in err_str or "invalid" in message and "key" in message:
            user_definition = "401: Невірний API ключ. Перевірте на aistudio.google.com/apikey"
            user_translation = err_str
        elif "429" in err_str or "rate limit" in message:
            user_definition = "429: Перевищено ліміт. Спробуйте через хвилину."
            user_translation = err_str
        elif "auth/config error" in err_str:
            user_definition = "Помилка доступу до Gemini API (key/model)."
            user_translation = err_str
        else:
            user_definition = err_str if len(err_str) < 150 else f"Gemini: {err_str[:140]}…"
            user_translation = "Спробуйте ще раз пізніше."
        info = fallback_info(str(e))
        info["definition"] = user_definition
        info["ukrainian"] = user_translation
        return info

# ─── KEYBOARDS ────────────────────────────────────────────────


def make_word_keyboard(word: str):
    buttons = [[InlineKeyboardButton("🖼 Картинки",
                                     url=f"https://www.google.com/search?q={word.replace(' ',
                                                                                         '+')}+meaning&tbm=isch"),
                InlineKeyboardButton("🔍 Значення",
                                     url=f"https://www.google.com/search?q={word.replace(' ',
                                                                                         '+')}+meaning"),
                ],
               [InlineKeyboardButton("➡️ Наступне слово",
                                     callback_data="next_word")],
               ]
    # Add mini app button if URL is configured
    if WEBAPP_URL and not WEBAPP_URL.startswith("https://YOUR_TUNNEL"):
        buttons.append([InlineKeyboardButton(
            "⚡ Відкрити English Zap", web_app=WebAppInfo(url=WEBAPP_URL))])
    return InlineKeyboardMarkup(buttons)


def make_level_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔰 Нульовий", callback_data="level_zero"),
            InlineKeyboardButton("🌱 Початківець", callback_data="level_beginner"),
        ],
        [
            InlineKeyboardButton("📘 Середній", callback_data="level_intermediate"),
            InlineKeyboardButton("🎓 Просунутий", callback_data="level_advanced"),
        ],
    ])


def make_main_menu_keyboard():
    rows = [
        [InlineKeyboardButton("⚡ Нове слово", callback_data="next_word"),
         InlineKeyboardButton("💬 Фраза", callback_data="next_phrase")],
        [InlineKeyboardButton("📊 Мій рівень", callback_data="show_level"),
         InlineKeyboardButton("📈 Статистика", callback_data="show_stats")],
    ]
    if WEBAPP_URL and not WEBAPP_URL.startswith("https://YOUR_TUNNEL"):
        rows.append([InlineKeyboardButton(
            "⚡ Відкрити English Zap", web_app=WebAppInfo(url=WEBAPP_URL))])
    return InlineKeyboardMarkup(rows)

# ─── CORE SEND ────────────────────────────────────────────────


async def build_and_send_word(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    content_type: str = "word",
):
    # Resolve user_id and send function
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat_id

        async def send(
            text, **kw): return await update.callback_query.message.reply_text(text, **kw)
    elif update.message:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        async def send(
            text, **kw): return await update.message.reply_text(text, **kw)
    else:
        user_id = update.effective_user.id if update.effective_user else OWNER_CHAT_ID
        chat_id = update.effective_chat.id if update.effective_chat else OWNER_CHAT_ID

        async def send(text,
                       **kw): return await context.bot.send_message(chat_id=chat_id,
                                                                    text=text,
                                                                    **kw)

    level = get_user_level(user_id)
    loading = await send(f"⚡ Завантажую {'слово' if content_type == 'word' else 'фразу'}…")

    try:
        if content_type == "phrase":
            word = await fetch_phrase_for_level(level)
        else:
            word = await fetch_word_for_level(level)
        info = await ask_gemini(word, level)
    except Exception as e:
        logger.error(f"[build_and_send] fetch error: {e}")
        await send("⚠️ Помилка генерації. Спробуйте ще раз.")
        try:
            await loading.delete()
        except BaseException:
            pass
        return

    # Save for webapp sync
    record_word_for_user(user_id, word, info, level)

    badge = {
        "zero": "🔰 Рівень: Нульовий",
        "beginner": "🌱 Рівень: Початківець",
        "intermediate": "📘 Рівень: Середній",
        "advanced": "🎓 Рівень: Просунутий",
    }.get(level, "🌱")

    try:
        await loading.delete()
    except BaseException:
        pass

    word_count = get_user_word_count(user_id)

    msg = (
        f"{badge}\n\n"
        f"{info['emoji']} {word.upper()}\n"
        f"{info['transcribe']} • {info['pron_ua']}\n\n"
        f"🇺🇦 {info['ukrainian']}\n\n"
        f"📖 Визначення:\n{info['definition']}\n\n"
        f"💬 Приклад:\n🇬🇧 {info['example']}\n🇺🇦 {info['example_uk']}\n\n"
        f"Слів у вашому словнику: {word_count}"
    )
    await send(msg, reply_markup=make_word_keyboard(word))

    # Voice: word
    try:
        audio = await text_to_voice(word)
        await context.bot.send_voice(
            chat_id=chat_id, voice=audio,
            caption=f"🔊 {word.upper()} • {info['transcribe']} • {info['pron_ua']}",
        )
    except Exception as e:
        logger.warning(f"[TTS word] {e}")
        await send("🔇 Озвучка слова тимчасово недоступна (Edge TTS).")

    # Voice: example sentence (skip if example is invalid/placeholder-like)
    example_text = (info.get("example") or "").strip()
    if len(example_text) >= 3 and example_text not in {"—", "-", "N/A"}:
        try:
            ex_audio = await text_to_voice(example_text)
            await context.bot.send_voice(
                chat_id=chat_id, voice=ex_audio,
                caption=f"📖 {example_text}",
            )
        except Exception as e:
            logger.warning(f"[TTS example] {e}")
            await send("🔇 Озвучка прикладу тимчасово недоступна (Edge TTS).")

# ─── HANDLERS ─────────────────────────────────────────────────


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name or "Учень"

    if str(user_id) not in user_levels and user_id not in user_levels:
        user_levels[str(user_id)] = "beginner"
    user_chat_ids.add(user_id)
    save_data()

    welcome = (
        f"⚡ Привіт, {name}! Це English Zap Bot!\n\n"
        f"Я надсилатиму тобі нові слова щодня та озвучуватиму їх.\n\n"
        f"📱 Твій Telegram ID: {user_id}\n"
        f"Введи його у налаштуваннях вебзастосунку для синхронізації.\n\n"
        f"Оберіть рівень 👇"
    )
    await update.message.reply_text(welcome, reply_markup=make_level_keyboard())


async def send_word_cmd(
    update, context): await build_and_send_word(
        update, context, "word")


async def send_phrase_cmd(
    update, context): await build_and_send_word(
        update, context, "phrase")


async def set_level(update, context):
    await update.message.reply_text("Оберіть рівень 👇", reply_markup=make_level_keyboard())


async def menu_command(update, context):
    await update.message.reply_text("⚡ *English Zap* — Головне меню:", parse_mode="Markdown", reply_markup=make_main_menu_keyboard())


async def stats_command(update, context):
    user_id = update.effective_user.id
    level = get_user_level(user_id)
    word_count = get_user_word_count(user_id)
    level_labels = {
        "zero": "🔰 Нульовий",
        "beginner": "🌱 Початківець",
        "intermediate": "📘 Середній",
        "advanced": "🎓 Просунутий"}
    await update.message.reply_text(
        f"📊 *Ваша статистика:*\n\n"
        f"👤 ID: `{user_id}`\n"
        f"📚 Рівень: {level_labels.get(level, level)}\n"
        f"📝 Слів у словнику: *{word_count}*\n\n"
        f"_Синхронізуйте з вебзастосунком за допомогою вашого ID_",
        parse_mode="Markdown",
    )


async def help_command(update, context):
    await update.message.reply_text(
        "*Команди English Zap:*\n\n"
        "/start — Запустити бота\n"
        "/word — Нове слово\n"
        "/phrase — Нова фраза\n"
        "/level — Змінити рівень\n"
        "/menu — Головне меню\n"
        "/stats — Ваша статистика\n"
        "/broadcast — Розсилка (власник)\n"
        "/sendall — Надіслати всім (власник)\n"
        "/help — Ця довідка",
        parse_mode="Markdown",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("level_"):
        level = data.replace("level_", "")
        user_levels[str(user_id)] = level
        save_data()
        info = {
            "zero": ("🔰", "Найпростіші слова та букви"),
            "beginner": ("🌱", "Прості слова повсякденного вжитку"),
            "intermediate": ("📘", "Корисна лексика для спілкування"),
            "advanced": ("🎓", "Складні та академічні слова"),
        }.get(level, ("🌱", ""))
        e, d = info
        await query.edit_message_text(
            f"{e} *Рівень обрано: {level}*\n_{d}_\n\nНадсилаю перше слово 👇",
            parse_mode="Markdown",
        )
        await build_and_send_word(update, context)

    elif data == "next_word":
        await build_and_send_word(update, context, "word")

    elif data == "next_phrase":
        await build_and_send_word(update, context, "phrase")

    elif data == "show_level":
        await query.edit_message_text("Оберіть новий рівень 👇", reply_markup=make_level_keyboard())

    elif data == "show_stats":
        level = get_user_level(user_id)
        word_count = get_user_word_count(user_id)
        level_labels = {
            "zero": "🔰 Нульовий",
            "beginner": "🌱 Початківець",
            "intermediate": "📘 Середній",
            "advanced": "🎓 Просунутий"}
        await query.edit_message_text(
            f"📊 *Ваша статистика:*\n\n"
            f"👤 Telegram ID: `{user_id}`\n"
            f"📚 Рівень: {level_labels.get(level, level)}\n"
            f"📝 Слів у словнику: *{word_count}*",
            parse_mode="Markdown",
            reply_markup=make_main_menu_keyboard(),
        )

# ─── ADMIN COMMANDS ───────────────────────────────────────────


async def broadcast_command(update, context):
    if update.effective_user.id != OWNER_CHAT_ID:
        await update.message.reply_text("⛔ Тільки для власника.")
        return
    if not context.args:
        await update.message.reply_text("Використання: /broadcast <текст>")
        return
    msg = " ".join(context.args)
    count = failed = 0
    for cid in list(user_chat_ids):
        try:
            await context.bot.send_message(chat_id=cid, text=msg)
            count += 1
            await asyncio.sleep(0.05)  # rate limit
        except TelegramError as e:
            logger.warning(f"[broadcast {cid}] {e}")
            failed += 1
    await update.message.reply_text(f"✅ Надіслано: {count} / Помилок: {failed}")


async def sendall_command(update, context):
    if update.effective_user.id != OWNER_CHAT_ID:
        await update.message.reply_text("⛔ Тільки для власника.")
        return
    ct = (context.args[0] if context.args else "word")
    if ct not in ("word", "phrase"):
        await update.message.reply_text("Використання: /sendall word|phrase")
        return

    count = failed = 0
    status_msg = await update.message.reply_text(f"⏳ Розпочинаю розсилку для {len(user_chat_ids)} користувачів…")

    for cid in list(user_chat_ids):
        try:
            # Create a minimal fake update pointing to this chat
            class FakeUser:
                id = cid
                first_name = ""

            class FakeChat:
                id = cid

            class FakeUpdate:
                effective_user = FakeUser()
                effective_chat = FakeChat()
                message = None
                callback_query = None

            await build_and_send_word(FakeUpdate(), context, ct)
            count += 1
            await asyncio.sleep(0.5)  # respectful rate limiting
        except Exception as e:
            logger.error(f"[sendall {cid}] {e}")
            failed += 1

    await status_msg.edit_text(f"✅ Розсилка завершена!\nНадіслано: {count} / Помилок: {failed}")

# ─── DAILY JOB ────────────────────────────────────────────────


async def daily_word_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Daily job: sending words to {len(user_chat_ids)} users")
    for cid in list(user_chat_ids):
        try:
            class FakeUser:
                id = cid

            class FakeChat:
                id = cid

            class FakeUpdate:
                effective_user = FakeUser()
                effective_chat = FakeChat()
                message = None
                callback_query = None
            await build_and_send_word(FakeUpdate(), context, "word")
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"[daily {cid}] {e}")

# ─── MAIN ─────────────────────────────────────────────────────


def main():
    async def post_init(app):
        commands = [
            BotCommand("start", "Запустити / перезапустити"),
            BotCommand("word", "Нове слово"),
            BotCommand("phrase", "Нова фраза"),
            BotCommand("level", "Змінити рівень"),
            BotCommand("menu", "Головне меню"),
            BotCommand("stats", "Ваша статистика"),
            BotCommand("help", "Довідка"),
        ]
        await app.bot.set_my_commands(commands)

        # Set Menu Button to open webapp (if URL is configured)
        if WEBAPP_URL and not WEBAPP_URL.startswith("https://YOUR_TUNNEL"):
            try:
                await app.bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(text="⚡ English Zap", web_app=WebAppInfo(url=WEBAPP_URL))
                )
                logger.info(f"Mini App menu button set: {WEBAPP_URL}")
            except Exception as e:
                logger.warning(f"Could not set menu button: {e}")

        # Daily word at 8:00 UTC
        if app.job_queue:
            app.job_queue.run_daily(
                daily_word_job, time=time(
                    hour=8, minute=0, tzinfo=timezone.utc))
            logger.info("✅ Daily job scheduled at 08:00 UTC")
        else:
            logger.warning("Job queue unavailable. Install with: pip install 'python-telegram-bot[job-queue]'")

    if not BOT_TOKEN:
        raise RuntimeError("Missing ENGLISH_ZAP_BOT_TOKEN environment variable.")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    for cmd, fn in [
        ("start", start),
        ("word", send_word_cmd),
        ("phrase", send_phrase_cmd),
        ("level", set_level),
        ("menu", menu_command),
        ("stats", stats_command),
        ("broadcast", broadcast_command),
        ("sendall", sendall_command),
        ("help", help_command),
    ]:
        app.add_handler(CommandHandler(cmd, fn))

    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("⚡ English Zap Bot v3 started!")
    logger.info(f"   Data file : {DATA_FILE.resolve()}")
    logger.info(f"   Words dir : {WORDS_DIR.resolve()}")
    logger.info(f"   Webapp    : {WEBAPP_URL}")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    main()
