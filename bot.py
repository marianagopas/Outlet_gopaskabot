import json
import os
import uuid
import asyncio
from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHAT_ID = -1003840384606     # канал джерела
TARGET_CHAT_ID = -1001321059832     # канал отримувача
SOURCE_USERNAME = "Gopaska_outlet" # username джерела без @
DRAFTS_FILE = "drafts.json"         # json для альбомів
# ================================================

# --- Завантаження чернеток ---
drafts = {}
if os.path.exists(DRAFTS_FILE) and os.path.getsize(DRAFTS_FILE) > 0:
    try:
        with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
            drafts = json.load(f)
    except json.JSONDecodeError:
        drafts = {}

def save_drafts():
    with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)

def log_forward(album_link, count):
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ALBUM | {count} items | {album_link}")

# --- Відправка альбому з підписом ---
async def send_album(context: ContextTypes.DEFAULT_TYPE, draft_id):
    draft = drafts.get(draft_id)
    if not draft or not draft.get("photos"):
        return

    # Відправляємо альбом
    media_group = [InputMediaPhoto(media=pid) for pid in draft["photos"]]
    await context.bot.send_media_group(chat_id=TARGET_CHAT_ID, media=media_group)

    # Підпис після альбому (посилання на перший пост альбому джерела)
    first_msg_id = draft["first_msg_id"]
    source_link = f"https://t.me/{SOURCE_USERNAME}/{first_msg_id}"
    await context.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text=f"<a href='{source_link}'>Переглянути джерело</a>",
        parse_mode="HTML"
    )

    log_forward(source_link, len(media_group))
    del drafts[draft_id]
    save_drafts()

# --- Ловимо повідомлення з каналу ---
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or msg.chat.id != SOURCE_CHAT_ID:
        return

    media_group_id = getattr(msg, "media_group_id", None)

    # --- Альбом ---
    if media_group_id:
        if media_group_id not in drafts:
            drafts[media_group_id] = {
                "photos": [],
                "first_msg_id": msg.message_id
            }

        if msg.photo:
            drafts[media_group_id]["photos"].append(msg.photo[-1].file_id)

        save_drafts()

        # Відправляємо альбом
        await send_album(context, media_group_id)
        return

    # --- Одиночне фото ---
    if msg.photo:
        first_msg_id = msg.message_id
        source_link = f"https://t.me/{SOURCE_USERNAME}/{first_msg_id}"
        await context.bot.send_photo(
            chat_id=TARGET_CHAT_ID,
            photo=msg.photo[-1].file_id,
            caption=f"<a href='{source_link}'>Переглянути джерело</a>",
            parse_mode="HTML"
        )
        log_forward(source_link, 1)

# --- Main ---
def main():
    if not os.path.exists(DRAFTS_FILE):
        open(DRAFTS_FILE, "w", encoding="utf-8").close()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
