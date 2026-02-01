import json
import os
from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHAT_ID = -1003840384606
TARGET_CHAT_ID = -1001321059832
SOURCE_USERNAME = "Gopaska_outlet"
DRAFTS_FILE = "drafts.json"
# ================================================

# ======== БУФЕР ДЛЯ АЛЬБОМІВ ========
drafts = {}              # media_group_id -> {"photos": [...], "first_msg_id": ...}
current_group_id = None # ОСТАННІЙ активний media_group_id

# --- Безпечне завантаження JSON ---
if os.path.exists(DRAFTS_FILE) and os.path.getsize(DRAFTS_FILE) > 0:
    try:
        with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
            drafts = json.load(f)
    except json.JSONDecodeError:
        drafts = {}

def save_drafts():
    with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)

async def send_album(context: ContextTypes.DEFAULT_TYPE, group_id):
    """Відправляє альбом + підпис і очищає буфер"""
    if group_id not in drafts:
        return

    album = drafts[group_id]
    media = [InputMediaPhoto(media=pid) for pid in album["photos"]]

    # 1️⃣ Надсилаємо альбом
    await context.bot.send_media_group(
        chat_id=TARGET_CHAT_ID,
        media=media
    )

    # 2️⃣ ПІДПИС ОДРАЗУ ПІСЛЯ ЦЬОГО АЛЬБОМУ
    first_msg_id = album["first_msg_id"]
    link = f"https://t.me/{SOURCE_USERNAME}/{first_msg_id}"

    await context.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text=f"<a href='{link}'>Переглянути джерело</a>",
        parse_mode="HTML"
    )

    # Очищаємо буфер
    del drafts[group_id]
    save_drafts()

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_group_id

    msg = update.effective_message
    if not msg or msg.chat.id != SOURCE_CHAT_ID:
        return

    new_group_id = getattr(msg, "media_group_id", None)

    # ======= АЛЬБОМ =======
    if new_group_id:
        # 🔹 Якщо прийшов НОВИЙ альбом — відправляємо попередній
        if current_group_id and current_group_id != new_group_id:
            await send_album(context, current_group_id)

        # Якщо це перше фото нового альбому — створюємо буфер
        if new_group_id not in drafts:
            drafts[new_group_id] = {
                "photos": [],
                "first_msg_id": msg.message_id
            }

        # Додаємо фото в альбом
        if msg.photo:
            drafts[new_group_id]["photos"].append(msg.photo[-1].file_id)

        save_drafts()
        current_group_id = new_group_id
        return

    # ======= ОДИНОЧНЕ ФОТО =======
    if msg.photo:
        # Якщо перед цим був альбом — спочатку закриваємо його
        if current_group_id:
            await send_album(context, current_group_id)
            current_group_id = None

        first_msg_id = msg.message_id
        link = f"https://t.me/{SOURCE_USERNAME}/{first_msg_id}"

        await context.bot.send_photo(
            chat_id=TARGET_CHAT_ID,
            photo=msg.photo[-1].file_id,
            caption=f"<a href='{link}'>Переглянути джерело</a>",
            parse_mode="HTML"
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
