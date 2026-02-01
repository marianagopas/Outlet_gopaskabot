import os
from datetime import datetime
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = "8567978239:AAFA0MrCVit7WkIyrMX2NxJ0Rxq6NvqD9O8"
SOURCE_CHAT_ID = -1003840384606     # канал джерела
TARGET_CHAT_ID = -1001321059832     # канал отримувача
SOURCE_USERNAME = "Gopaska_outlet" # username джерела без @
LOG_FILE = "forward_log.txt"        # лог файл
# ================================================

# Поточний альбом
current_album = None  # {"media_group_id": str, "media": list, "first_msg_id": int}

def log_forward(message_type: str, link: str, count: int = 1):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message_type} | {count} items | {link}\n"
    print(entry.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

async def send_album(album, context: ContextTypes.DEFAULT_TYPE):
    """Відправляє альбом та підпис після збору"""
    if not album or not album["media"]:
        return

    # Відправка альбому
    await context.bot.send_media_group(
        chat_id=TARGET_CHAT_ID,
        media=album["media"]
    )

    # Підпис після альбому з клікабельним посиланням на перший пост альбому джерела
    source_link = f"https://t.me/{SOURCE_USERNAME}/{album['first_msg_id']}"
    await context.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text=f"<a href='{source_link}'>Переглянути джерело</a>",
        parse_mode="HTML"
    )

    log_forward("ALBUM", source_link, len(album["media"]))

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_album
    msg = update.channel_post
    if not msg or msg.chat.id != SOURCE_CHAT_ID:
        return

    group_id = getattr(msg, "media_group_id", None)

    # ===== Альбом =====
    if group_id:
        # Якщо новий альбом — закриваємо поточний
        if not current_album or group_id != current_album.get("media_group_id"):
            if current_album:
                await send_album(current_album, context)
            # Створюємо новий альбом
            current_album = {
                "media_group_id": group_id,
                "media": [],
                "first_msg_id": msg.message_id
            }

        # Додаємо фото/відео в альбом
        if msg.photo:
            current_album["media"].append(InputMediaPhoto(media=msg.photo[-1].file_id))
        elif msg.video:
            current_album["media"].append(InputMediaVideo(media=msg.video.file_id))
        return

    # ===== Одиночне фото/відео/текст =====
    source_link = f"https://t.me/{SOURCE_USERNAME}/{msg.message_id}"
    caption = f"<a href='{source_link}'>Переглянути джерело</a>"

    if msg.photo:
        await context.bot.send_photo(
            chat_id=TARGET_CHAT_ID,
            photo=msg.photo[-1].file_id,
            caption=caption,
            parse_mode="HTML"
        )
        log_forward("PHOTO", source_link)
    elif msg.video:
        await context.bot.send_video(
            chat_id=TARGET_CHAT_ID,
            video=msg.video.file_id,
            caption=caption,
            parse_mode="HTML"
        )
        log_forward("VIDEO", source_link)
    elif msg.text:
        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=f"{msg.text}\n\n<a href='{source_link}'>Переглянути джерело</a>",
            parse_mode="HTML"
        )
        log_forward("TEXT", source_link)

def main():
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, "w", encoding="utf-8").close()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Бот запущений...")
    app.run_polling()

if __name__ == "__main__":
    main()
